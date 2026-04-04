JSON 腳本引擎
==============

MailThunder 內建強大的 JSON 腳本引擎，讓您無需撰寫 Python 程式碼即可自動化郵件工作流程。
引擎建構於 ``Executor`` 類別之上，將命令名稱對映到 Python 可呼叫物件。

----

運作原理
--------

1. 您撰寫一個包含 ``auto_control`` 鍵的 JSON 檔案（或字典）
2. 值是一個動作命令列表
3. 每個命令由 ``Executor`` 依序執行
4. 結果被收集並以字典形式回傳

.. code-block:: text

   JSON 動作檔
       │
       ▼
   execute_action(action_list)
       │
       ├── 若為 dict: 提取 action_list["auto_control"]
       ├── 若為 list: 直接使用
       │
       ▼
   對每個動作 in action_list:
       │
       ├── action = ["command_name"]          ──▶ executor.event_dict["command_name"]()
       ├── action = ["command_name", {k: v}]  ──▶ executor.event_dict["command_name"](**{k: v})
       └── action = ["command_name", [a, b]]  ──▶ executor.event_dict["command_name"](*[a, b])

----

動作檔格式
----------

動作檔使用 ``auto_control`` 鍵包含命令列表：

.. code-block:: json

   {
     "auto_control": [
       ["command_name"],
       ["command_name", {"key": "value"}],
       ["command_name", ["arg1", "arg2"]]
     ]
   }

**參數慣例：**

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - 格式
     - 類型
     - Python 對應
   * - ``["command"]``
     - 無參數
     - ``command()``
   * - ``["command", {"k": "v"}]``
     - 關鍵字參數
     - ``command(**{"k": "v"})``
   * - ``["command", ["a", "b"]]``
     - 位置參數
     - ``command(*["a", "b"])``

您也可以直接傳入純列表（不含 ``auto_control`` 包裝）給 ``execute_action()``：

.. code-block:: python

   from je_mail_thunder import execute_action

   execute_action([
       ["MT_smtp_later_init"],
       ["smtp_quit"]
   ])

----

內建命令
--------

**SMTP 命令：**

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - 命令
     - 說明
   * - ``MT_smtp_later_init``
     - 初始化並登入 SMTP 伺服器
   * - ``MT_smtp_create_message_and_send``
     - 建立並寄送純文字郵件
   * - ``MT_smtp_create_message_with_attach_and_send``
     - 建立並寄送附件郵件
   * - ``smtp_quit``
     - 斷開 SMTP 連線

**IMAP 命令：**

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - 命令
     - 說明
   * - ``MT_imap_later_init``
     - 初始化並登入 IMAP 伺服器
   * - ``MT_imap_select_mailbox``
     - 選擇信箱（預設：INBOX）
   * - ``MT_imap_search_mailbox``
     - 搜尋並取得原始郵件資料
   * - ``MT_imap_mail_content_list``
     - 取得解析後的郵件內容列表
   * - ``MT_imap_output_all_mail_as_file``
     - 匯出所有郵件為本地檔案
   * - ``MT_imap_quit``
     - 斷開 IMAP 連線

**認證命令：**

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - 命令
     - 說明
   * - ``MT_set_mail_thunder_os_environ``
     - 設定認證環境變數
   * - ``MT_get_mail_thunder_os_environ``
     - 取得目前認證環境變數

**套件管理：**

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - 命令
     - 說明
   * - ``MT_add_package_to_executor``
     - 載入 Python 套件至執行器

**Python 內建函式：**

所有 Python 內建函式（``print``、``len``、``range``、``type``、``str``、
``int``、``list``、``dict`` 等）自動註冊，可作為命令使用。

----

範例
----

**寄送純文字郵件：**

.. code-block:: json

   {
     "auto_control": [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
         "message_content": "Hello from the scripting engine!",
         "message_setting_dict": {
           "Subject": "自動化郵件",
           "To": "receiver@gmail.com",
           "From": "sender@gmail.com"
         }
       }],
       ["smtp_quit"]
     ]
   }

**讀取並匯出所有郵件：**

.. code-block:: json

   {
     "auto_control": [
       ["MT_imap_later_init"],
       ["MT_imap_select_mailbox"],
       ["MT_imap_output_all_mail_as_file"],
       ["MT_imap_quit"]
     ]
   }

**搜尋未讀郵件（唯讀模式）：**

.. code-block:: json

   {
     "auto_control": [
       ["MT_imap_later_init"],
       ["MT_imap_select_mailbox", {"mailbox": "INBOX", "readonly": true}],
       ["MT_imap_mail_content_list", {"search_str": "UNSEEN"}],
       ["MT_imap_quit"]
     ]
   }

**設定認證後寄送：**

.. code-block:: json

   {
     "auto_control": [
       ["MT_set_mail_thunder_os_environ", {
         "mail_thunder_user": "sender@gmail.com",
         "mail_thunder_user_password": "your_app_password"
       }],
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
         "message_content": "透過腳本設定認證！",
         "message_setting_dict": {
           "Subject": "認證測試",
           "To": "receiver@gmail.com",
           "From": "sender@gmail.com"
         }
       }],
       ["smtp_quit"]
     ]
   }

----

執行動作檔
----------

**從 Python：**

.. code-block:: python

   from je_mail_thunder import execute_action, read_action_json

   # 執行單一檔案
   result = execute_action(read_action_json("/path/to/action.json"))

   # 結果是一個 dict，將 "execute: [action]" 對映到回傳值
   for action, return_value in result.items():
       print(action, return_value)

**執行目錄中的多個檔案：**

.. code-block:: python

   from je_mail_thunder import execute_files, get_dir_files_as_list

   # 取得目錄中所有 .json 檔案
   files = get_dir_files_as_list("/path/to/actions/")
   results = execute_files(files)

**從命令列：**

.. code-block:: bash

   # 執行單一檔案
   python -m je_mail_thunder -e /path/to/action.json

   # 執行目錄中所有 JSON 檔案
   python -m je_mail_thunder -d /path/to/actions/

   # 執行 JSON 字串
   python -m je_mail_thunder --execute_str '[["print", ["Hello!"]]]'

----

擴充自訂命令
------------

將您自己的函式加入執行器：

.. code-block:: python

   from je_mail_thunder import add_command_to_executor, execute_action

   def send_notification(channel, message):
       print(f"[{channel}] {message}")
       return {"status": "sent", "channel": channel}

   # 註冊自訂命令
   add_command_to_executor({
       "notify": send_notification,
   })

   # 在動作列表中使用
   execute_action([
       ["notify", {"channel": "#alerts", "message": "處理完成"}]
   ])

.. warning::

   僅可加入 ``types.MethodType`` 和 ``types.FunctionType`` 實體。
   傳入非可呼叫物件（如字串或整數）將引發 ``AddCommandException``。

----

執行輸出
--------

執行動作時，每個命令及其回傳值會印出到 stdout：

.. code-block:: text

   execute: ['MT_smtp_later_init']
   None
   execute: ['MT_smtp_create_message_and_send', {...}]
   None
   execute: ['smtp_quit']
   None

若動作失敗，例外會被捕獲、記錄並存入結果字典。
執行器 **不會** 在錯誤時停止 — 會繼續執行後續動作並收集所有結果。

----

執行緒安全
----------

``Executor`` 類別以模組級別單例（``executor``）實體化。
JSON 檔案讀取（``read_action_json``）使用 ``threading.Lock`` 確保執行緒安全的檔案存取。
但執行器的 ``event_dict`` 本身未加鎖，因此應避免並發修改命令註冊表。
