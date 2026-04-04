專案模板
========

MailThunder 可以建立一個新的專案目錄，包含預建模板檔案，
讓您擁有可立即使用的郵件自動化起點。

----

建立專案
--------

**從 Python：**

.. code-block:: python

   from je_mail_thunder import create_project_dir

   # 在目前工作目錄建立，使用預設名稱 "MailThunder"
   create_project_dir()

   # 在指定路徑建立，使用自訂名稱
   create_project_dir(project_path="/path/to/projects", parent_name="MyMailProject")

**從命令列：**

.. code-block:: bash

   python -m je_mail_thunder -c /path/to/project

**參數：**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - 參數
     - 預設值
     - 說明
   * - ``project_path``
     - ``os.getcwd()``
     - 建立專案資料夾的目錄
   * - ``parent_name``
     - ``"MailThunder"``
     - 專案根目錄名稱

----

產生的結構
----------

.. code-block:: text

   MyMailProject/
     keyword/
       keyword1.json          # SMTP 寄送郵件模板
       keyword2.json          # IMAP 讀取並匯出模板
       bad_keyword_1.json     # 套件載入範例（安全性警告）
     executor/
       executor_one_file.py   # 執行單一動作檔
       executor_folder.py     # 執行目錄中所有動作檔
       executor_bad_file.py   # 不良做法範例（安全性警告）

----

模板檔案：keyword/
--------------------

**keyword1.json** — SMTP 寄送郵件模板：

.. code-block:: json

   [
     ["MT_smtp_later_init"],
     ["MT_smtp_create_message_and_send", {
       "message_content": "test",
       "message_setting_dict": {
         "Subject": "test_subject",
         "To": "example@gmail.com",
         "From": "example@gmail.com"
       }
     }],
     ["smtp_quit"]
   ]

**keyword2.json** — IMAP 讀取並匯出模板：

.. code-block:: json

   [
     ["MT_imap_later_init"],
     ["MT_imap_select_mailbox"],
     ["MT_imap_output_all_mail_as_file"]
   ]

**bad_keyword_1.json** — 套件載入範例：

.. code-block:: json

   [
     ["MT_add_package_to_executor", ["os"]],
     ["os_system", ["python --version"]],
     ["os_system", ["python -m pip --version"]]
   ]

.. warning::

   ``bad_keyword_1.json`` 展示如何將 ``os`` 套件載入執行器，這使得腳本引擎
   可以執行任意系統命令。此範例作為教育用途，展示在正式環境中 **不應該** 做的事。
   在處理不受信任的輸入時，切勿載入 ``os``、``subprocess`` 或類似套件。

----

模板檔案：executor/
---------------------

**executor_one_file.py** — 執行單一動作檔：

.. code-block:: python

   from je_mail_thunder import execute_action, read_action_json

   execute_action(
       read_action_json(
           r"/path/to/MyMailProject/keyword/keyword1.json"
       )
   )

**executor_folder.py** — 執行目錄中所有 JSON 動作檔：

.. code-block:: python

   from je_mail_thunder import execute_files, get_dir_files_as_list

   execute_files(
       get_dir_files_as_list(
           r"/path/to/MyMailProject/keyword"
       )
   )

**executor_bad_file.py** — 不良做法範例：

.. code-block:: python

   # 此範例主要用於提醒使用者驗證輸入的重要性。
   from je_mail_thunder import execute_action, read_action_json

   execute_action(
       read_action_json(
           r"/path/to/MyMailProject/keyword/bad_keyword_1.json"
       )
   )

.. note::

   模板原始碼中的 ``{temp}`` 佔位符在專案建立時會被替換為實際的絕對路徑。

----

自訂模板
--------

建立完成後，您可以自由修改產生的檔案：

1. 編輯 ``keyword/*.json`` 檔案以符合您的郵件工作流程
2. 更新郵件地址、主旨和內容
3. 在 ``keyword/`` 目錄新增 ``.json`` 動作檔
4. 修改 ``executor/*.py`` 檔案以加入錯誤處理或自訂邏輯

**範例：新增工作流程**

建立 ``keyword/weekly_report.json``：

.. code-block:: json

   {
     "auto_control": [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_with_attach_and_send", {
         "message_content": "請查看附件的週報。",
         "message_setting_dict": {
           "Subject": "週報",
           "To": "team@company.com",
           "From": "reporter@company.com"
         },
         "attach_file": "/data/reports/weekly.pdf",
         "use_html": false
       }],
       ["smtp_quit"]
     ]
   }

執行：

.. code-block:: bash

   python -m je_mail_thunder -e MyMailProject/keyword/weekly_report.json
