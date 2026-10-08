認證設定
========

MailThunder 以密碼或 OAuth2 登入。當呼叫 ``later_init()`` 或
``try_to_login_with_env_or_content()`` 時，有 OAuth2 設定就用它，否則用帳號密碼：
先嘗試 JSON 設定檔，若找不到則使用環境變數。

認證流程
--------

.. code-block:: text

   later_init() 被呼叫
       │
       ▼
   有 OAuth2 設定嗎？（mail_thunder_content.json 的 "oauth2"，否則 mail_thunder_oauth2_* 環境變數）
       │
       ├── 有 ──▶ 存取權杖（快取的，或在權杖端點更新）──▶ AUTH XOAUTH2
       │
       ▼ 沒有
   讀取目前工作目錄的 mail_thunder_content.json
       │
       ├── 找到檔案且包含 "user" + "password"
       │       │
       │       ▼
       │   使用檔案認證資訊登入 ─── 成功 ──▶ 完成 (login_state = True)
       │                          │
       │                          └── 失敗 ──▶ 記錄錯誤
       │
       └── 找不到檔案或無效
               │
               ▼
           讀取環境變數：mail_thunder_user + mail_thunder_user_password
               │
               ├── 環境變數已設定
               │       │
               │       ▼
               │   使用環境變數登入 ─── 成功 ──▶ 完成 (login_state = True)
               │                       │
               │                       └── 失敗 ──▶ 記錄錯誤
               │
               └── 環境變數未設定 ──▶ 記錄錯誤

方式一：JSON 設定檔
--------------------

在 **目前工作目錄** 建立名為 ``mail_thunder_content.json`` 的檔案：

.. code-block:: json

   {
     "user": "your_email@gmail.com",
     "password": "your_app_password"
   }

.. warning::

   此檔案包含您的郵件認證資訊（明文）。請勿將其提交到版本控制系統。
   請將 ``mail_thunder_content.json`` 加入 ``.gitignore``。

**內部運作方式：**

1. ``read_output_content()`` 檢查 ``Path.cwd()`` 中是否存在 ``mail_thunder_content.json``
2. 若找到，讀取 JSON 並更新 ``mail_thunder_content_data_dict``
3. ``user`` 和 ``password`` 值傳遞給 ``smtplib.SMTP_SSL.login()``
   或 ``imaplib.IMAP4_SSL.login()``

方式二：環境變數
-----------------

**選項 A — 在 Python 中於執行期設定：**

.. code-block:: python

   from je_mail_thunder import set_mail_thunder_os_environ

   set_mail_thunder_os_environ(
       mail_thunder_user="your_email@gmail.com",
       mail_thunder_user_password="your_app_password"
   )

此呼叫 ``os.environ.update()`` 設定兩個環境變數：

- ``mail_thunder_user``
- ``mail_thunder_user_password``

**選項 B — 在終端機中設定：**

.. code-block:: bash

   # Linux / macOS
   export mail_thunder_user="your_email@gmail.com"
   export mail_thunder_user_password="your_app_password"

.. code-block:: batch

   :: Windows CMD
   set mail_thunder_user=your_email@gmail.com
   set mail_thunder_user_password=your_app_password

.. code-block:: powershell

   # Windows PowerShell
   $env:mail_thunder_user = "your_email@gmail.com"
   $env:mail_thunder_user_password = "your_app_password"

**取得目前環境變數值：**

.. code-block:: python

   from je_mail_thunder import get_mail_thunder_os_environ

   creds = get_mail_thunder_os_environ()
   # 回傳: {"mail_thunder_user": "...", "mail_thunder_user_password": "..."}

方式三：OAuth2（Google 與 Microsoft）
--------------------------------------

Google 與 Microsoft 都在淘汰郵件的密碼登入。使用 OAuth2 時，MailThunder 在服務商的權杖端點以 refresh token
換取短效的存取權杖（只用標準函式庫，且必須是 ``https``），快取到到期前一分鐘，再以 SASL ``XOAUTH2`` 登入。
有 OAuth2 設定時，以它取代密碼。client ID、client secret 與 refresh token 要先透過服務商的授權流程取得一次
（Google Cloud 的 OAuth 用戶端，或 Microsoft Entra 的應用程式註冊）；MailThunder 不執行那個流程。

**在** ``mail_thunder_content.json`` **中**\ （``user`` 也可以放在 ``oauth2`` 裡）：

.. code-block:: json

   {
     "user": "you@example.com",
     "oauth2": {
       "provider": "microsoft",
       "client_id": "...",
       "client_secret": "...",
       "refresh_token": "...",
       "tenant": "common"
     }
   }

**或用環境變數：** ``mail_thunder_user`` 加上 ``mail_thunder_oauth2_provider``、``mail_thunder_oauth2_client_id``、
``mail_thunder_oauth2_client_secret`` 與 ``mail_thunder_oauth2_refresh_token``；選用 ``mail_thunder_oauth2_tenant``、
``mail_thunder_oauth2_scope``、``mail_thunder_oauth2_token_url``，或以 ``mail_thunder_oauth2_access_token`` 直接使用給定的權杖。

.. list-table::
   :header-rows: 1

   * - 服務商
     - SMTP
     - IMAP
     - 要求的範圍
   * - ``google``\ （預設）
     - ``smtp.gmail.com:465``，隱含式 TLS（``SMTPWrapper``）
     - ``imap.gmail.com``
     - ``https://mail.google.com/``
   * - ``microsoft``
     - ``smtp.office365.com:587``，STARTTLS（``SMTPStartTLSWrapper``）
     - ``outlook.office365.com``
     - ``https://outlook.office.com/`` 上的 ``SMTP.Send`` 與 ``IMAP.AccessAsUser.All``，以及 ``offline_access``

``smtp_instance`` 與 ``imap_instance``（以及 ``MT_smtp_*``／``MT_imap_*`` 指令）會連到設定所指服務商的伺服器。
``SMTPStartTLSWrapper`` 在送出任何其他內容前先以 ``STARTTLS`` 升級，並拒絕不提供它的伺服器。其他服務商可用
``token_url``（與 ``scope``），再以它的主機自行建立 wrapper。client secret 與權杖不會出現在日誌、錯誤訊息或設定的
``repr`` 裡。

.. code-block:: python

   from je_mail_thunder import OAuth2Settings, SMTPStartTLSWrapper, oauth2_token_cache

   settings = OAuth2Settings(user="you@contoso.com", provider="microsoft", client_id="...",
                             client_secret="...", refresh_token="...", tenant="contoso.onmicrosoft.com")
   with SMTPStartTLSWrapper() as smtp:
       smtp.oauth2_login(settings.user, oauth2_token_cache.access_token(settings))

認證物件
--------

每一種登入方式都是一個 ``Authentication`` 物件，因此負責連線的程式不需要在意拿到的是哪一種。

.. list-table::
   :header-rows: 1
   :widths: 38 42 20

   * - 類別
     - 登入方式
     - 適用於
   * - ``PasswordAuth(user, password)``
     - 帳號的密碼
     - SMTP、IMAP
   * - ``AppPasswordAuth(user, app_password)``
     - 應用程式密碼（Google、Yahoo、iCloud）。顯示時夾帶的空白會被去除
     - SMTP、IMAP
   * - ``OAuth2Auth(settings)``
     - OAuth2 存取權杖，以 ``Authorization: Bearer ...`` 送出
     - HTTP API
   * - ``XOAUTH2Auth(settings)``
     - 同一個權杖，以 SASL ``XOAUTH2`` 送出
     - SMTP、IMAP、HTTP API

.. code-block:: python

   from je_mail_thunder import AppPasswordAuth, OAuth2Settings, SMTPWrapper, XOAUTH2Auth, resolve_authentication

   auth = AppPasswordAuth("you@gmail.com", "abcd efgh ijkl mnop")
   auth = XOAUTH2Auth(OAuth2Settings(user="you@gmail.com", client_id="...",
                                     client_secret="...", refresh_token="..."))
   auth = resolve_authentication()   # 設定檔或環境變數裡的登入方式，沒有則為 None

   with SMTPWrapper() as smtp:
       auth.login(smtp)              # 同一個呼叫也能登入 IMAPWrapper

- ``auth.login(client)`` 登入 SMTP 或 IMAP wrapper。
- ``auth.authorization()`` 回傳 HTTP ``Authorization`` 標頭的值。
- ``auth.user`` 是帳號的位址，``auth.mechanism`` 是機制的名稱
  （``"password"``、``"app-password"``、``"oauth2"``、``"xoauth2"``）。

機制做不到被要求的事情時會引發 ``MailThunderAuthenticationException``：
密碼沒有 HTTP 授權，單純的 ``OAuth2Auth`` 不能登入郵件伺服器（請用 ``XOAUTH2Auth``）。
``MailThunderOAuth2Exception`` 現在是它的子類別。

``settings`` 是 ``OAuth2Settings``\ （見方式三）。權杖來自共用的 ``oauth2_token_cache``，
除非另外給類別自己的 ``token_cache``；權杖會在到期前一分鐘更新。

``resolve_authentication()`` 回傳設定檔或環境變數裡的登入方式：有 OAuth2 設定時是 ``XOAUTH2Auth``，
否則是 ``PasswordAuth``，都沒有則為 ``None``。找到的 OAuth2 設定不完整時會引發 ``MailThunderOAuth2Exception``。

密碼與權杖不會出現在 ``repr``、日誌或例外訊息中。

從程式提供認證資訊
------------------

登入讀的是 ``mail_thunder_content.json`` 或環境變數，不是 ``mail_thunder_content_data_dict``：那個字典是
``write_output_content()`` 寫進檔案的內容。認證資訊來自金鑰庫或資料庫時，請設定環境變數
（``set_mail_thunder_os_environ``），或填好字典後呼叫 ``write_output_content()``\ （檔案會以明文保存它們）。

Gmail 特殊設定
--------------

如果您使用 Gmail，有兩個額外需求：

1. **使用應用程式密碼** — Gmail 不允許使用一般 Google 帳戶密碼登入。
   您必須產生應用程式密碼：

   - 前往 `Google 應用程式密碼 <https://myaccount.google.com/apppasswords>`_
   - 選擇「郵件」和您的裝置
   - 複製產生的 16 字元密碼
   - 使用此密碼作為 ``password`` 值

2. **啟用 IMAP** (讀取郵件時需要) — Gmail 預設停用 IMAP 存取：

   - 前往 Gmail 設定 > 查看所有設定 > 轉寄和 POP/IMAP
   - 在「IMAP 存取」下，選擇「啟用 IMAP」
   - 儲存變更

.. note::

   應用程式密碼需要您的 Google 帳戶啟用兩步驟驗證。

檢查登入狀態 (SMTP)
---------------------

``SMTPWrapper`` 透過 ``login_state`` 屬性追蹤認證狀態：

.. code-block:: python

   from je_mail_thunder import SMTPWrapper

   smtp = SMTPWrapper()
   print(smtp.login_state)  # False

   success = smtp.try_to_login_with_env_or_content()
   print(smtp.login_state)  # 登入成功則為 True
   print(success)           # True 或 False

透過 JSON 腳本引擎設定
-----------------------

在 JSON 動作檔中設定認證資訊：

.. code-block:: json

   {
     "mail_thunder": [
       ["MT_set_mail_thunder_os_environ", {
         "mail_thunder_user": "your_email@gmail.com",
         "mail_thunder_user_password": "your_app_password"
       }],
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
         "message_content": "Hello!",
         "message_setting_dict": {
           "Subject": "測試",
           "From": "your_email@gmail.com",
           "To": "receiver@gmail.com"
         }
       }],
       ["MT_smtp_quit"]
     ]
   }
