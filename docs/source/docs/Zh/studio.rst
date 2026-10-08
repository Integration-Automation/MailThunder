MailThunder Studio
==================

MailThunder Studio 是一個在本機開啟的頁面，用來查看並試用郵件 API 目前的設定：帳號、模板、觸發器、
附件政策、專案的郵件層與日誌。它由標準函式庫提供服務，不需要額外的套件，而且只會呼叫核心 API
（:doc:`mail_api`），所以不論使用哪一家供應商都一樣運作。

.. code-block:: bash

   python -m je_mail_thunder.studio

.. code-block:: text

   MailThunder Studio: http://localhost:9947/#token=mL0n...
   Anyone with this address can use the mailbox while Studio runs. Ctrl+C stops it.

頁面會在瀏覽器中開啟。角落的按鈕可以在 English 與中文之間切換。

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 選項
     - 意義
   * - ``--host HOST``
     - 要綁定的位址。預設為 ``localhost``；其他位址會讓該網路上的人都能使用這個信箱
   * - ``--port PORT``
     - 要綁定的埠號（9947）
   * - ``--project DIR``
     - 使用這個專案的郵件層（:doc:`project_mail_layer`）。這會執行它的 ``mail/config.py`` 與 ``mail/triggers.py``
   * - ``--no-browser``
     - 只印出位址，不開啟瀏覽器

從 Python 啟動：

.. code-block:: python

   from je_mail_thunder import Mail
   from je_mail_thunder.studio.server import start_studio

   server = start_studio(Mail(provider="microsoft_graph"))    # 在 daemon 執行緒上執行
   print(server.url)
   ...
   server.stop()

----

頁面
----

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - 頁面
     - 顯示與可執行的內容
   * - 儀表板
     - 帳號（供應商、使用者、登入機制；絕不顯示密碼或權杖）、每個供應商的健康狀態、模板／處理函式／
       觸發器後端的數量、最新的稽核紀錄，以及一個可以寄信的表單
   * - 帳號
     - 帳號與它連線的伺服器、可以選用的供應商名稱，以及要求每個供應商連線並登入的按鈕
   * - 模板
     - 模板目錄與每個模板及其變數；可以輸入 JSON 格式的 context 產生內容，不會寄出
   * - 觸發器
     - 事件名稱、已訂閱的處理函式與其過濾條件、觸發器後端與狀態，以及立即查看一次新郵件的按鈕
   * - 政策
     - 附件政策；可以修改，變更在 Studio 執行期間有效
   * - 專案
     - 專案目錄的郵件層：有哪些檔案與模板。不會執行其中任何檔案
   * - 日誌
     - MailThunder 日誌檔的結尾，以及稽核日誌
   * - 設定
     - MailThunder 存放檔案的位置、已註冊的供應商，以及執行環境的版本

Studio 會在它顯示的 ``Mail`` 上掛上稽核日誌與健康監控（:doc:`monitoring`），
所以從頁面寄出的郵件與其他郵件一樣會被記錄。

----

安全性
------

Studio 可以寄信也可以讀取日誌，因此它被設計成只給坐在這台電腦前的人使用的工具：

- 除非以 ``--host`` 指定，否則只綁定 ``localhost``。
- 每個 API 請求都必須帶著伺服器啟動時產生的隨機權杖。權杖放在印出位址的 fragment（``#`` 之後），
  瀏覽器不會把它送給任何伺服器，也不會放進 ``Referer``。
- ``Host`` 標頭不是 Studio 啟動位址的請求會被拒絕，所以同一個瀏覽器中開啟的其他網頁無法透過別的名稱連到它。
- 頁面不會從其他地方載入任何 script 或樣式（``Content-Security-Policy``）、不能被嵌入框架，
  而且所有內容都以文字寫入、絕不當成標記：透過郵件送來的主旨或寄件者無法在瀏覽器中執行。
- 任何回應都不包含密碼、權杖或 client secret。
- 從頁面寄出的郵件不能指定附件，所以無法利用頁面把這台電腦上的檔案寄出去。請求內容上限為 1 MiB。

不使用時請停止 Studio。它不適合在共用的電腦上長時間執行，也不適合放在公開的位址之後。

----

頁面背後的 API
--------------

頁面呼叫的是 ``je_mail_thunder.studio.api.StudioApi``。每個方法都接收並回傳可轉成 JSON 的值，
所以也可以在測試或其他前端中使用。

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - 請求
     - ``StudioApi`` 方法
   * - ``GET /api/dashboard``
     - ``dashboard()``
   * - ``GET /api/accounts``、``POST /api/accounts/check``
     - ``accounts()``、``check_accounts()``
   * - ``GET /api/templates``、``POST /api/templates/render``
     - ``templates()``、``render_template({"name", "context"})``
   * - ``GET /api/triggers``、``POST /api/triggers/poll``
     - ``triggers()``、``poll_triggers()``
   * - ``GET /api/policies``、``POST /api/policies``
     - ``policies()``、``set_policy({...})``
   * - ``GET /api/projects``
     - ``projects()``
   * - ``GET /api/logs?lines=200``
     - ``logs({"lines": 200})``
   * - ``GET /api/settings``
     - ``settings()``
   * - ``POST /api/send``
     - ``send({"to", "cc", "bcc", "subject", "text", "html", "sender", "reply_to", "template", "context"})``

請求需要帶 ``X-MailThunder-Token`` 標頭。MailThunder 的錯誤會以 HTTP 400 與
``{"error": "<例外名稱>", "message": "..."}`` 回應；權杖缺少或錯誤、``Host`` 不正確時則回應 403。
