例外處理
========

MailThunder 為不同的錯誤情境定義了一組自訂例外類別。
所有例外都繼承自基底 ``MailThunderException`` 類別。

----

例外階層
--------

.. code-block:: text

   Exception (Python 內建)
     └── MailThunderException
           ├── MailThunderJsonException
           ├── MailThunderContentException
           ├── MailThunderArgparseException
           ├── ExecuteActionException
           ├── AddCommandException
           └── JsonActionException

----

例外參考
--------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - 例外
     - 引發時機
   * - ``MailThunderException``
     - 所有 MailThunder 錯誤的基底例外。不會直接引發。
   * - ``MailThunderJsonException``
     - JSON 格式化失敗（無效的 JSON ��料或型別錯誤）
   * - ``MailThunderContentException``
     - 讀取或寫入 ``mail_thunder_content.json`` 時發生錯誤
   * - ``MailThunderArgparseException``
     - CLI 未收到有效參數或收到未知函式
   * - ``ExecuteActionException``
     - 執行器收到無效的動作格式、空動作列表或錯誤的資料型別
   * - ``AddCommandException``
     - ``add_command_to_executor()`` 收到非可呼叫值（非函式/方法）
   * - ``JsonActionException``
     - 找不到 JSON 動作檔或無法儲存

----

錯誤標籤
--------

每個例外都關聯一個人類可讀的錯誤標籤字串，定義在
``je_mail_thunder.utils.exception.exception_tags``：

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - 錯誤標籤
     - 訊息
   * - ``mail_thunder_cant_reformat_json_error``
     - ``"Can't reformat json is type right?"``
   * - ``mail_thunder_wrong_json_data_error``
     - ``"Can't parser json"``
   * - ``mail_thunder_content_set_compiler_error``
     - ``"When set compiler using content make an error"``
   * - ``mail_thunder_content_file_error``
     - ``"MailThunder content file error"``
   * - ``mail_thunder_content_login_failed``
     - ``"can't login with mail thunder content"``
   * - ``mail_thunder_argparse_get_wrong_function``
     - ``"get unknown function"``
   * - ``add_command_exception``
     - ``"command value type should be as method or function"``
   * - ``executor_list_error``
     - ``"executor receive wrong data list is none or wrong type"``
   * - ``cant_execute_action_error``
     - ``"cant execute action"``
   * - ``cant_find_json_error``
     - ``"cant find json file"``
   * - ``cant_save_json_error``
     - ``"cant save json file"``
   * - ``action_is_null_error``
     - ``"json action is null"``

----

捕獲例外
--------

您可以在程式碼中捕獲 MailThunder 例外：

.. code-block:: python

   from je_mail_thunder import execute_action
   from je_mail_thunder.utils.exception.exceptions import (
       MailThunderException,
       ExecuteActionException,
       JsonActionException,
   )

   try:
       execute_action([["nonexistent_command"]])
   except ExecuteActionException as e:
       print(f"執行器錯誤: {e}")
   except MailThunderException as e:
       print(f"MailThunder 錯誤: {e}")

.. note::

   大多數 MailThunder 方法（特別是 ``SMTPWrapper`` 和 ``IMAPWrapper``）
   會在內部捕獲例外並記錄，而非向上傳播。例外更常由執行器、JSON 檔案工具
   和 CLI 元件引發。
