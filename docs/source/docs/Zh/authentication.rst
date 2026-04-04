認證設定
========

MailThunder 支援兩種認證方式。當呼叫 ``later_init()`` 或
``try_to_login_with_env_or_content()`` 時，系統會先嘗試 JSON 設定檔，
若找不到則使用環境變數。

認證流程
--------

.. code-block:: text

   later_init() 被呼叫
       │
       ▼
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

方式三：手動注入認證資訊
-------------------------

您可以在呼叫登入前直接更新全域認證字典：

.. code-block:: python

   from je_mail_thunder import mail_thunder_content_data_dict

   mail_thunder_content_data_dict.update({
       "user": "your_email@gmail.com",
       "password": "your_app_password",
   })

這在認證資訊來自金鑰庫、資料庫或其他外部來源的程式化情境中很有用。

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
     "auto_control": [
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
       ["smtp_quit"]
     ]
   }
