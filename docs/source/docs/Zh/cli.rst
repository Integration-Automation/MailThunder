命令列介面
==========

MailThunder 透過 ``python -m je_mail_thunder`` 提供命令列介面 (CLI)，
可直接從終端機執行 JSON 動作檔、JSON 字串和建立專案。

----

使用方式
--------

.. code-block:: bash

   python -m je_mail_thunder [選項]

----

選項
----

.. list-table::
   :header-rows: 1
   :widths: 10 25 65

   * - 旗標
     - 完整旗標
     - 說明
   * - ``-e``
     - ``--execute_file``
     - 執行單一 JSON 動作檔
   * - ``-d``
     - ``--execute_dir``
     - 執行目錄中所有 JSON 動作檔
   * -
     - ``--execute_str``
     - 直接執行 JSON 字串
   * - ``-c``
     - ``--create_project``
     - 建立包含模板的專案目錄

若未提供任何旗標，CLI 會引發 ``MailThunderArgparseException``。

----

執行單一動作檔
--------------

.. code-block:: bash

   python -m je_mail_thunder -e /path/to/action.json

讀取 JSON 檔案、解析動作列表，並傳遞給 ``execute_action()``。

----

執行目錄中所有檔案
------------------

.. code-block:: bash

   python -m je_mail_thunder -d /path/to/actions/

掃描目錄中所有 ``.json`` 檔案（使用 ``get_dir_files_as_list()``），
並透過 ``execute_files()`` 依序執行。

----

執行 JSON 字串
---------------

.. code-block:: bash

   python -m je_mail_thunder --execute_str '[["print", ["Hello from CLI!"]]]'

解析 JSON 字串並直接執行。

.. note::

   **Windows 注意事項：** 在 Windows 平台（``win32``、``cygwin``、``msys``），
   JSON 字串會被雙重解析（``json.loads`` 呼叫兩次）以處理 shell 跳脫字元差異。

   在 Linux/macOS 上，單引號直接可用：

   .. code-block:: bash

      python -m je_mail_thunder --execute_str '[["print", ["Hello!"]]]'

----

建立專案
--------

.. code-block:: bash

   python -m je_mail_thunder -c /path/to/project

在指定路徑建立包含模板檔案的專案目錄。
詳見 :doc:`project_templates`。

----

結束代碼
--------

- **0** — 所有動作執行成功
- **1** — 發生錯誤（例外訊息印出到 ``stderr``）

----

範例
----

**從命令列寄送郵件：**

.. code-block:: bash

   # 建立 JSON 動作檔
   cat > send.json << 'EOF'
   {
     "auto_control": [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
         "message_content": "Hello from CLI!",
         "message_setting_dict": {
           "Subject": "CLI 測試",
           "To": "receiver@gmail.com",
           "From": "sender@gmail.com"
         }
       }],
       ["smtp_quit"]
     ]
   }
   EOF

   # 執行
   python -m je_mail_thunder -e send.json

**執行多個動作檔：**

.. code-block:: bash

   mkdir -p actions/
   cp send.json actions/
   cp read.json actions/
   python -m je_mail_thunder -d actions/

**建立新專案：**

.. code-block:: bash

   python -m je_mail_thunder -c /home/user/projects
   # 建立 /home/user/projects/MailThunder/ 包含模板
