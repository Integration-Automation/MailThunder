套件管理器
==========

MailThunder 的 ``PackageManager`` 允許您在執行期動態載入任何已安裝的 Python 套件
至腳本執行器，使其所有函式、內建函式和類別可作為動作命令使用。

----

運作原理
--------

當呼叫 ``MT_add_package_to_executor`` 並傳入套件名稱時：

1. ``importlib.find_spec()`` 檢查套件是否已安裝
2. ``importlib.import_module()`` 匯入該套件
3. ``inspect.getmembers()`` 提取所有函式、內建函式和類別
4. 每個成員以 ``{套件名稱}_{成員名稱}`` 命名慣例註冊至執行器的 ``event_dict``

.. code-block:: text

   MT_add_package_to_executor("os")
       │
       ▼
   find_spec("os") → 找到
       │
       ▼
   import_module("os")
       │
       ▼
   getmembers(os, isfunction)  → os_getcwd, os_listdir, os_makedirs, ...
   getmembers(os, isbuiltin)   → os_system, os_open, os_close, ...
   getmembers(os, isclass)     → os_error, ...
       │
       ▼
   全部註冊至 executor.event_dict

----

在 JSON 腳本中使用
-------------------

.. code-block:: json

   {
     "auto_control": [
       ["MT_add_package_to_executor", ["os"]],
       ["os_system", ["echo Hello from os.system"]],
       ["os_getcwd"]
     ]
   }

.. code-block:: json

   {
     "auto_control": [
       ["MT_add_package_to_executor", ["json"]],
       ["json_dumps", [{"key": "value"}]]
     ]
   }

----

在 Python 中使用
-----------------

.. code-block:: python

   from je_mail_thunder import execute_action

   execute_action([
       ["MT_add_package_to_executor", ["math"]],
       ["math_sqrt", [144]],
       ["math_factorial", [10]]
   ])

----

命名慣例
--------

所有成員以套件名稱和底線為前綴：

.. code-block:: text

   套件 "os"    → os_system, os_getcwd, os_path, os_listdir, ...
   套件 "json"  → json_dumps, json_loads, json_dump, json_load, ...
   套件 "math"  → math_sqrt, math_ceil, math_floor, math_factorial, ...

此做法防止套件之間以及與內建命令的名稱衝突。

----

已載入套件快取
--------------

``PackageManager`` 在 ``installed_package_dict`` 中快取已載入的套件。
若套件已被載入，後續對同一套件名稱呼叫 ``MT_add_package_to_executor``
會重用快取的匯入，而非重新匯入。

----

載入的內容
----------

從每個套件提取三種類別的成員：

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - 類別
     - 偵測方式
     - 範例
   * - 函式
     - ``inspect.isfunction``
     - ``os.getcwd``、``json.dumps``
   * - 內建函式
     - ``inspect.isbuiltin``
     - ``os.system``、``os.open``
   * - 類別
     - ``inspect.isclass``
     - ``os.error``、``json.JSONDecodeError``

.. note::

   子模組 **不會** 自動載入。例如，載入 ``os`` 不會自動使 ``os.path``
   的函式可用。您需要另外載入 ``os.path``：

   .. code-block:: json

      {
        "auto_control": [
          ["MT_add_package_to_executor", ["os.path"]],
          ["os.path_join", ["/home", "user", "file.txt"]]
        ]
      }

----

安全性警告
----------

.. warning::

   **將 ``os``、``subprocess``、``shutil`` 或 ``sys`` 等套件載入執行器，
   會授予腳本引擎存取系統層級操作的權限。**

   在以下情境中這是重大安全風險：

   - 處理不受信任的 JSON 動作檔
   - 將 Socket 伺服器暴露給外部客戶端
   - 在多租戶環境中運行

   **最佳做法：**

   - 僅載入您明確需要的套件
   - 在正式環境中切勿載入系統套件（``os``、``subprocess``、``sys``）
   - 驗證和過濾所有輸入
   - 不要將 Socket 伺服器暴露給不受信任的網路
   - 執行前審查 JSON 動作檔
